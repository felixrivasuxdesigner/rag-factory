-- Migration 001: Add rate_limits field to data_sources
-- This allows each source to have custom rate limiting configuration

-- Add rate_limits JSONB column to data_sources table
ALTER TABLE data_sources
ADD COLUMN IF NOT EXISTS rate_limits JSONB DEFAULT NULL;

-- Add comment explaining the field
COMMENT ON COLUMN data_sources.rate_limits IS
'Rate limiting configuration as JSON. Example:
{
  "requests_per_day": 5000,
  "requests_per_hour": 500,
  "min_delay": 1.0,
  "burst_limit": 5,
  "retry_after_429": true,
  "preset": "congress_api_demo"
}';

-- Add index for faster queries (though not critical for this field)
CREATE INDEX IF NOT EXISTS idx_data_sources_rate_limits
ON data_sources USING GIN (rate_limits);
