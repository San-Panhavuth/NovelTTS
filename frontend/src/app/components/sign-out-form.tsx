import { signOut } from "@/app/auth/actions";

export function SignOutForm() {
  return (
    <form action={signOut}>
      <button type="submit" className="rounded-md border px-3 py-2 text-sm">
        Sign out
      </button>
    </form>
  );
}