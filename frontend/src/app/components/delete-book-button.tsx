"use client";

import { useRef } from "react";
import { deleteBook } from "@/app/books/actions";

export function DeleteBookButton({ bookId }: { bookId: string }) {
  const formRef = useRef<HTMLFormElement>(null);

  function handleClick() {
    if (window.confirm("Delete this book? This cannot be undone.")) {
      formRef.current?.requestSubmit();
    }
  }

  return (
    <form ref={formRef} action={deleteBook}>
      <input type="hidden" name="bookId" value={bookId} />
      <button
        type="button"
        onClick={handleClick}
        className="rounded-lg border border-red-200 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-950"
      >
        Delete book
      </button>
    </form>
  );
}
