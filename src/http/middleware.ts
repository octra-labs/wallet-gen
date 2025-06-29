export function handleErrors<T extends any[]>(
  fn: (...args: T) => Promise<Response>
) {
  return async function (...args: T): Promise<Response> {
    try {
      return await fn(...args);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "An unexpected error occurred.";
      return Response.json({ success: false, error: message }, { status: 500 });
    }
  };
}
