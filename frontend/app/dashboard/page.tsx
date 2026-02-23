import { auth } from "@/lib/auth"
import { redirect } from "next/navigation"
import Link from "next/link"
import { SignOutButton } from "@/components/SignOutButton"

export default async function DashboardPage() {
  const session = await auth()

  if (!session) {
    redirect("/")
  }

  return (
    <div className="min-h-screen bg-zinc-50">
      {/* Nav */}
      <nav className="bg-white border-b border-zinc-100 px-8 py-4 flex items-center justify-between">
        <span className="text-lg font-semibold tracking-tight">Travel Planner</span>
        <div className="flex items-center gap-4">
          <span className="text-sm text-zinc-500">{session.user?.email}</span>
          <SignOutButton />
        </div>
      </nav>

      <main className="max-w-4xl mx-auto px-6 py-16">
        <h1 className="text-3xl font-bold text-zinc-900">
          Welcome back{session.user?.name ? `, ${session.user.name.split(" ")[0]}` : ""}
        </h1>
        <p className="mt-2 text-zinc-500">Where do you want to go?</p>

        {/* Trip request input — placeholder for next phase */}
        <div className="mt-10 rounded-2xl border border-zinc-200 bg-white p-8 shadow-sm">
          <p className="text-sm font-medium text-zinc-500 mb-3">Coming soon</p>
          <p className="text-zinc-700">
            Trip booking will be available once the search and booking agent is
            connected. Check back after Week 4.
          </p>
          <Link
            href="/profile"
            className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-zinc-900 underline underline-offset-4"
          >
            Update your traveler profile &rarr;
          </Link>
        </div>
      </main>
    </div>
  )
}
