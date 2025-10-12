# RAG Factory - Backlog & Issues

## 🐛 Bugs & Issues

### High Priority

#### Issue #1: Database Connection Timeout on Large Documents
**Status**: Open
**Priority**: High
**Reported**: 2025-10-11
**Affected Component**: Worker, Vector DB Writer

**Description**:
When processing very large documents (>10MB, generating >10k chunks), the PostgreSQL connection times out and closes during embedding generation, causing subsequent documents to fail.

**Example Case**:
- Document 635193: 12.2 MB → 15,715 chunks
- Document 635194: 3 MB → 3,899 chunks
- Connection closes during processing, all subsequent inserts fail

**Current Behavior**:
- Worker generates all chunks successfully
- Connection times out during embedding/insertion phase
- Error: `psycopg2.InterfaceError: connection already closed`
- All subsequent documents fail until worker restart

**Impact**:
- Job must be cancelled and restarted
- Large documents cannot be processed
- Wastes processing time on embeddings that fail to save

**Proposed Solutions**:

1. **Batch Processing with Connection Refresh** (Recommended)
   - Process large documents in batches (e.g., 1000 chunks at a time)
   - Refresh database connection between batches
   - Commit after each batch to prevent data loss

2. **Connection Pool with Keep-Alive**
   - Implement connection pooling
   - Add periodic keep-alive queries
   - Set appropriate connection timeout values

3. **Document Size Limit**
   - Add configurable max document size
   - Split mega-documents at ingestion time
   - Process as multiple logical documents

4. **Streaming Inserts**
   - Stream embeddings to database as they're generated
   - Don't accumulate all in memory
   - Use COPY or bulk insert in smaller batches

**Implementation Priority**: High
- Blocks ingestion of large legal documents
- Common in legal/technical documentation

**Related Files**:
- `backend/services/vector_db_writer.py` - Connection management
- `backend/workers/ingestion_tasks.py` - Batch processing
- `backend/processors/adaptive_chunker.py` - Chunking strategy

#### Issue #2: Job Restart Creates New Job Instead of Reusing ID
**Status**: Open
**Priority**: Medium
**Reported**: 2025-10-12
**Affected Component**: API, Job Management

**Description**:
When using the restart endpoint on a cancelled/failed job, it creates a new job with a new ID instead of restarting the original job. This makes it harder to track job history and creates confusion in the UI.

**Current Behavior**:
- `POST /jobs/278/restart` creates Job 280 (new ID)
- Original Job 278 remains in "cancelled" status
- User loses continuity of job history

**Expected Behavior**:
- `POST /jobs/278/restart` should reuse Job 278
- Update status from "cancelled" → "queued" → "running"
- Preserve job ID for better tracking

**Impact**:
- Clutters job list with duplicate entries
- Makes job history harder to follow
- User confusion about which job is which

**Proposed Solution**:
- Modify restart endpoint to reuse existing job ID
- Reset job counters and status
- Update `started_at` and clear `completed_at`
- Re-enqueue to Redis with same job ID

**Related Files**:
- `backend/api/main.py` - Restart endpoint (line ~826)
- `backend/workers/ingestion_tasks.py` - Job execution

---

#### Issue #3: Job Progress Not Updating in UI for Running Jobs
**Status**: Open
**Priority**: Medium
**Reported**: 2025-10-12
**Affected Component**: Worker, API, Frontend

**Description**:
Jobs created via the restart endpoint show `total_documents: 0` and `processed_documents: 0` in the API, even though the worker is actively processing documents. This prevents the UI from showing progress bars or completion percentages.

**Current Behavior**:
- Job 279 processing document 4966/5889 (84% complete)
- API shows: `total_documents: 0, processed_documents: 0`
- UI cannot display progress

**Root Cause**:
- Worker is not updating job progress in `ingestion_jobs` table
- Progress tracking code may not be running for restarted jobs
- `total_documents` set during fetch phase, but fetch returns 0 for incremental syncs

**Impact**:
- User cannot monitor job progress in real-time
- No way to estimate completion time
- Poor user experience for long-running jobs

**Proposed Solution**:
1. Update worker to track progress during document processing loop
2. Periodically update `processed_documents` counter
3. Set `total_documents` correctly even for incremental syncs
4. Add progress percentage calculation in API response

**Related Files**:
- `backend/workers/ingestion_tasks.py` - Progress tracking (lines ~230-280)
- `backend/api/main.py` - Job status endpoint (line ~600)
- `frontend/src/components/JobMonitor.tsx` - Progress display

#### Issue #4: Connector Re-downloads All Documents on Every Job
**Status**: ✅ Resolved
**Priority**: High
**Reported**: 2025-10-12
**Resolved**: 2025-10-12
**Affected Component**: Connectors, Job Management

**Description**:
Every time a new job is created, the connector re-downloads ALL documents from the source (e.g., 5889 documents from BCN Chile), even if they were already downloaded in previous jobs. This causes significant performance degradation and wastes bandwidth.

**Current Behavior**:
- Job 280 created → Connector queries SPARQL → Downloads 5889 XMLs from BCN
- Job 281 created → Connector queries SPARQL → Downloads 5889 XMLs AGAIN
- Each job re-fetches all documents from scratch
- No caching or reuse of previously downloaded content

**Impact**:
- **Performance**: 15-20 minutes wasted downloading same documents
- **Bandwidth**: Unnecessary load on BCN Chile servers
- **Rate limiting**: Risk of hitting API rate limits
- **User experience**: Jobs take much longer than necessary

**Root Cause**:
- Connectors fetch documents fresh on each job execution
- No document cache or content store
- Deduplication only happens AFTER download (in processing phase)
- Incremental sync fetches metadata but still downloads full XMLs

**Proposed Solutions**:

1. **Document Content Cache** (Recommended)
   - Cache downloaded XML/content in internal database
   - Add `documents_content` table with: hash, source_id, content, downloaded_at
   - Reuse cached content if hash matches
   - Refresh only if modified date changed

2. **Connector-Level Deduplication**
   - Check `documents_tracking` before downloading
   - Skip download if document already completed
   - Only fetch new/modified documents

3. **Incremental Fetch with Content**
   - Store last successful fetch timestamp per source
   - Query only documents modified since last fetch
   - For BCN: Use FILTER(?date > last_fetch_date) in SPARQL

**Implementation Priority**: High
- Blocking efficient re-runs and incremental updates
- Wastes significant time on large document sets
- Critical for production use

**Related Files**:
- `backend/connectors/chile_bcn_connector.py` - BCN connector fetch logic
- `backend/connectors/base_connector.py` - Base connector interface
- `backend/workers/ingestion_tasks.py` - Job execution and fetch phase
- `backend/core/schema.py` - Add documents_content table

**Metrics**:
- Job 280-327: 47 jobs created by restart bug
- Each would re-download 5889 documents
- Total wasted downloads: ~277,000 documents
- Estimated wasted time: ~12 hours of downloading

**Resolution** (2025-10-12):
✅ **Implemented Solution #1: Document Content Cache**

**What was implemented:**
1. **Database**: New table `documents_content_cache` with:
   - Full content storage with SHA-256 hash
   - Access tracking (access_count, last_accessed_at)
   - Source metadata and URLs
   - Optimized indexes for fast lookups

2. **Service**: `ContentCacheService` with methods:
   - `get_cached_content()` - Retrieves from cache (updates stats)
   - `save_to_cache()` - Saves with automatic upsert
   - `get_cache_stats()` - Usage statistics
   - `clear_old_cache()` - Automatic cleanup

3. **Connector Integration**: Modified `ChileBCNConnector`:
   - Checks cache BEFORE downloading XML
   - Saves automatically after successful download
   - Logs cache hits/misses with statistics
   - Reports cache hit rate at job completion

4. **Worker Integration**: Updated `ingestion_tasks.py`:
   - Initializes cache service automatically
   - Passes cache to supported connectors (chile_bcn, us_congress)
   - Transparent operation without API changes

**Performance Impact:**
- Before: 15-20 min downloading 5889 documents every job
- After: Cache hit = <1 sec per document
- Expected: 90-95% reduction in download time on re-runs
- Ideal for: Job restarts, incremental syncs, scheduled jobs

**Branch**: `feature/document-content-cache` → `main` → `journey-law-production`
**Commits**: c3ff05c, 757237b

---

## 🚀 Feature Requests

### Completed

#### Feature: Job Control (Cancel/Delete/Restart)
**Status**: ✅ Completed
**Branch**: `feature/job-control` (merged to `journey-law-production`)
**Priority**: High
**Completed**: 2025-10-12

**Description**: Add comprehensive job control functionality to manage long-running ingestion jobs.

**Features Implemented**:
- ✅ Cancel running jobs (POST /jobs/{id}/cancel)
- ✅ Delete completed/failed jobs (DELETE /jobs/{id})
- ✅ Restart failed or cancelled jobs (POST /jobs/{id}/restart)
- ✅ Individual controls per job (not global)
- ✅ Worker cancellation check in processing loop
- ✅ Frontend UI buttons with color-coded actions:
  - Red cancel button for running/pending/queued jobs
  - Blue restart button for failed/cancelled jobs
  - Gray delete button for completed/failed/cancelled jobs

**Known Issues**:
- See Issue #2: Restart creates new job ID
- See Issue #3: Progress not updating for restarted jobs

**Next Steps**:
- Fix restart behavior to reuse job ID
- Fix progress tracking for restarted jobs
- Create PR to merge to `main` for community benefit

#### Feature: Job Control UI Improvements
**Status**: ✅ Completed
**Branch**: `feature/job-ui-improvements`
**Priority**: Medium
**Started**: 2025-10-12
**Completed**: 2025-10-12
**Affected Component**: Frontend

**Description**:
Replace browser-native `alert()` and `confirm()` dialogs with user-friendly Toast notifications and Modal confirmation dialogs for job control actions (cancel, restart, delete).

**Completed Tasks**:
1. ✅ Created `Toast.tsx` component for notifications
   - Success, error, warning, info variants
   - Auto-dismiss with configurable duration (default 5s)
   - Close button with smooth animations
   - Phosphor icons integration
   - Slide-in animation from right

2. ✅ Created `ConfirmDialog.tsx` component for confirmations
   - Modal overlay with backdrop click handling
   - Customizable title, message, button text
   - Variant support (danger, primary, warning)
   - Accessible close button
   - Fade-in animation

3. ✅ Created `useToast` custom hook
   - Toast state management
   - showToast() helper method
   - ToastContainer component
   - Auto-cleanup on dismiss

4. ✅ Integrated into `JobMonitor.tsx`
   - Replaced all 3 `alert()` calls with toast notifications
   - Replaced all 3 `confirm()` calls with ConfirmDialog modal
   - Added ToastContainer to component render
   - Added conditional ConfirmDialog render

5. ✅ Added comprehensive CSS styles in `App.css`
   - Toast notification styles with variants
   - Modal dialog refinements
   - Job action button colors (cancel, restart, delete)
   - Mobile-responsive breakpoints
   - Smooth animations

**Implementation Summary**:
```typescript
// useToast hook integration:
const { showToast, ToastContainer } = useToast()
const [confirmDialog, setConfirmDialog] = useState<ConfirmDialogState | null>(null)

// Toast notifications:
showToast('Job cancelled successfully!', 'success')
showToast('Failed to cancel job. Please try again.', 'error')

// Confirmation dialogs:
setConfirmDialog({
  title: 'Cancel Job',
  message: `Are you sure you want to cancel Job #${jobId}?`,
  variant: 'danger',
  onConfirm: async () => { /* action */ }
})
```

**User Experience Improvements**:
- ✨ No more intrusive browser alerts blocking UI
- ✨ Beautiful toast notifications with auto-dismiss
- ✨ Elegant modal confirmations with clear actions
- ✨ Color-coded job actions (red=cancel, blue=restart, gray=delete)
- ✨ Smooth animations and transitions
- ✨ Mobile-responsive design
- ✨ Accessible close buttons

**Related Files**:
- `frontend/src/components/Toast.tsx`
- `frontend/src/components/ConfirmDialog.tsx`
- `frontend/src/hooks/useToast.tsx`
- `frontend/src/components/JobMonitor.tsx` (integrated)
- `frontend/src/App.css` (styles added)

**Build Status**:
- ✅ TypeScript compilation successful
- ✅ Production build successful (341.12 kB gzipped)
- ✅ No type errors

**Next Steps**:
- Test in browser with live backend
- Merge to `main` branch
- Create PR for community

---

## 📝 Technical Debt

### Medium Priority

1. **Connection Management**
   - Implement proper connection pooling
   - Add connection health checks
   - Handle reconnection gracefully

2. **Error Recovery**
   - Better error handling for network failures
   - Retry logic for transient errors
   - Preserve partial progress on failures

3. **Performance Optimization**
   - Parallel embedding generation for large documents
   - Optimize chunk size based on document characteristics
   - Cache embeddings for duplicate content

---

## 💡 Future Enhancements

### Low Priority

1. **Incremental Large Document Processing**
   - Process large documents incrementally
   - Resume from last successful chunk
   - Progress tracking at chunk level

2. **Resource Management**
   - Memory usage limits
   - CPU throttling for background jobs
   - Disk space monitoring

3. **Monitoring & Observability**
   - Real-time job progress dashboard
   - Performance metrics
   - Error rate tracking
   - Resource usage graphs

---

**Last Updated**: 2025-10-12
**Maintainer**: Felix Rivas (@felixrivasuxdesigner)
