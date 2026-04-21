"use server";

import { headers } from "next/headers";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { createSupabaseServerClient, isSupabaseConfigured } from "@/lib/supabase";

function toTrimmedValue(formData: FormData, key: string): string {
  const raw = formData.get(key);
  return typeof raw === "string" ? raw.trim() : "";
}

function ensureSupabaseConfigured(redirectPath: string) {
  if (!isSupabaseConfigured()) {
    redirect(`${redirectPath}?message=Supabase env is not configured.`);
  }
}

async function getRequestOrigin(): Promise<string> {
  const h = await headers();
  const forwardedProto = h.get("x-forwarded-proto");
  const forwardedHost = h.get("x-forwarded-host");
  const host = forwardedHost ?? h.get("host");
  const proto = forwardedProto ?? "http";

  if (host) {
    return `${proto}://${host}`;
  }

  return process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
}

export async function signInWithPassword(formData: FormData) {
  ensureSupabaseConfigured("/login");

  const email = toTrimmedValue(formData, "email");
  const password = toTrimmedValue(formData, "password");
  const supabase = await createSupabaseServerClient();

  const { error } = await supabase.auth.signInWithPassword({ email, password });

  if (error) {
    redirect(`/login?message=${encodeURIComponent(error.message)}`);
  }

  revalidatePath("/", "layout");
  redirect("/");
}

export async function signUpWithPassword(formData: FormData) {
  ensureSupabaseConfigured("/login");

  const email = toTrimmedValue(formData, "email");
  const password = toTrimmedValue(formData, "password");
  const origin = await getRequestOrigin();
  const emailRedirectTo = `${origin}/auth/callback`;
  const supabase = await createSupabaseServerClient();

  const { error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      emailRedirectTo,
    },
  });

  if (error) {
    redirect(`/login?message=${encodeURIComponent(error.message)}`);
  }

  redirect("/login?message=Check your email to confirm your account.");
}

export async function requestPasswordReset(formData: FormData) {
  ensureSupabaseConfigured("/forgot-password");

  const email = toTrimmedValue(formData, "email");
  const origin = await getRequestOrigin();
  const supabase = await createSupabaseServerClient();

  const { error } = await supabase.auth.resetPasswordForEmail(email, {
    redirectTo: `${origin}/auth/callback`,
  });

  if (error) {
    redirect(`/forgot-password?message=${encodeURIComponent(error.message)}`);
  }

  redirect("/forgot-password?message=Password reset email sent.");
}

export async function signInWithGoogle(formData: FormData) {
  ensureSupabaseConfigured("/login");

  const origin = await getRequestOrigin();
  const supabase = await createSupabaseServerClient();
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo: `${origin}/auth/callback`,
    },
  });

  if (error || !data.url) {
    redirect("/login?message=Unable to start Google sign-in.");
  }

  redirect(data.url);
}

export async function signOut() {
  ensureSupabaseConfigured("/login");

  const supabase = await createSupabaseServerClient();
  await supabase.auth.signOut();
  revalidatePath("/", "layout");
  redirect("/login");
}
