import { useEffect } from 'react'
import { CheckCircle, XCircle, Info, Warning, X } from '@phosphor-icons/react'

export type ToastType = 'success' | 'error' | 'info' | 'warning'

interface ToastProps {
  message: string
  type: ToastType
  onClose: () => void
  duration?: number
}

export default function Toast({ message, type, onClose, duration = 5000 }: ToastProps) {
  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(onClose, duration)
      return () => clearTimeout(timer)
    }
  }, [duration, onClose])

  const getIcon = () => {
    switch (type) {
      case 'success':
        return <CheckCircle size={20} weight="fill" />
      case 'error':
        return <XCircle size={20} weight="fill" />
      case 'warning':
        return <Warning size={20} weight="fill" />
      case 'info':
        return <Info size={20} weight="fill" />
    }
  }

  return (
    <div className={`toast toast-${type}`}>
      <div className="toast-icon">{getIcon()}</div>
      <div className="toast-message">{message}</div>
      <button className="toast-close" onClick={onClose} aria-label="Close">
        <X size={16} weight="bold" />
      </button>
    </div>
  )
}
