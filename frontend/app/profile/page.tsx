import { auth } from "@/lib/auth"
import { redirect } from "next/navigation"
import { ProfileForm } from "@/components/ProfileForm"
import Link from "next/link"

async function getProfile(email: string) {
  try {
    const res = await fetch(
      `${process.env.BACKEND_URL}/profile`,
      {
        headers: {
          "x-user-email": email,
          "x-api-key": process.env.INTERNAL_API_KEY!,
        },
        cache: "no-store",
      }
    )
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export default async function ProfilePage() {
  const session = await auth()

  if (!session?.user?.email) {
    redirect("/")
  }

  const profile = await getProfile(session.user.email)

  return (
    <div className="min-h-screen bg-zinc-50">
      <nav className="bg-white border-b border-zinc-100 px-8 py-4 flex items-center justify-between">
        <Link href="/dashboard" className="text-lg font-semibold tracking-tight hover:opacity-70 transition">
          Travel Planner
        </Link>
        <span className="text-sm text-zinc-500">{session.user.email}</span>
      </nav>

      <main className="max-w-2xl mx-auto px-6 py-16">
        <h1 className="text-3xl font-bold text-zinc-900">Traveler Profile</h1>
        <p className="mt-2 text-zinc-500">
          Your info is stored once and used on every booking. Sensitive fields
          are encrypted at rest.
        </p>
        <div className="mt-10">
          <ProfileForm initialData={profile} />
        </div>
      </main>
    </div>
  )
}
