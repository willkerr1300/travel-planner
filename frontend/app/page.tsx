import { SignInButton } from "@/components/SignInButton"

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* Nav */}
      <nav className="px-8 py-5 flex items-center justify-between border-b border-zinc-100">
        <span className="text-xl font-semibold tracking-tight">Travel Planner</span>
        <SignInButton />
      </nav>

      {/* Hero */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 text-center">
        <h1 className="text-5xl font-bold tracking-tight text-zinc-900 max-w-2xl leading-tight">
          Book your whole trip with one sentence.
        </h1>
        <p className="mt-6 text-xl text-zinc-500 max-w-xl leading-relaxed">
          Tell the AI where you want to go. It searches flights, hotels, and
          activities, then books everything — no tabs, no re-entering your info,
          no hand-offs.
        </p>
        <div className="mt-10">
          <SignInButton large />
        </div>

        {/* Feature grid */}
        <div className="mt-24 grid grid-cols-1 sm:grid-cols-3 gap-8 max-w-3xl w-full text-left">
          <Feature
            title="Plain-English requests"
            description='Type "fly me to Tokyo in October, 10 days, under $3,000" and the agent handles the rest.'
          />
          <Feature
            title="Compare full itineraries"
            description="Get 2–3 complete options with total cost breakdowns — not just flight prices."
          />
          <Feature
            title="One-click booking"
            description="Approve an itinerary and the agent completes every booking using your stored info."
          />
        </div>
      </main>

      <footer className="py-8 text-center text-sm text-zinc-400">
        Travel Planner &mdash; powered by AI
      </footer>
    </div>
  )
}

function Feature({
  title,
  description,
}: {
  title: string
  description: string
}) {
  return (
    <div className="p-6 rounded-xl border border-zinc-100 bg-zinc-50">
      <h3 className="font-semibold text-zinc-900">{title}</h3>
      <p className="mt-2 text-sm text-zinc-500 leading-relaxed">{description}</p>
    </div>
  )
}
