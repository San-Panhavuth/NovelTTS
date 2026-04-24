import { signOut } from "@/app/auth/actions";

export function SignOutForm() {
  return (
    <form action={signOut}>
      <button
        type="submit"
        className="rounded-md px-3 py-1.5 text-xs text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900 dark:hover:bg-zinc-800 dark:hover:text-zinc-100"
      >
        Sign out
      </button>
    </form>
  );
}
