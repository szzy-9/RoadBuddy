export default function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="error-message" role="alert">
      <span aria-hidden="true">!</span>
      <p>{message}</p>
    </div>
  )
}

