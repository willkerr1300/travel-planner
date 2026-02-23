import { auth } from "@/lib/auth"
import { NextRequest, NextResponse } from "next/server"

const BACKEND_URL = process.env.BACKEND_URL!
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY!

// GET /api/profile — fetch the current user's profile from FastAPI
export async function GET() {
  const session = await auth()
  if (!session?.user?.email) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 })
  }

  const res = await fetch(`${BACKEND_URL}/profile`, {
    headers: {
      "x-user-email": session.user.email,
      "x-api-key": INTERNAL_API_KEY,
    },
    cache: "no-store",
  })

  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}

// POST /api/profile — create or update the current user's profile
export async function POST(req: NextRequest) {
  const session = await auth()
  if (!session?.user?.email) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 })
  }

  const body = await req.json()

  const res = await fetch(`${BACKEND_URL}/profile`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-user-email": session.user.email,
      "x-api-key": INTERNAL_API_KEY,
    },
    body: JSON.stringify(body),
  })

  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
