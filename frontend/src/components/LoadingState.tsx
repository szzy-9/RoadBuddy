export default function LoadingState({ message = 'Checking your route and conditions…' }: { message?: string }) {
  return (
    <div className="loading-state" role="status" aria-live="polite">
      <span className="loading-spinner" aria-hidden="true" />
      <div>
        <strong>{message}</strong>
        <p>This can take a few seconds.</p>
      </div>
    </div>
  )
}

