import { auth } from "@/lib/auth"
import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

export default auth((req) => {
  const { pathname } = req.nextUrl

  // If the user is not signed in and tries to access a protected route,
  // redirect them to the landing page
  if (!req.auth && pathname !== "/") {
    return NextResponse.redirect(new URL("/", req.url))
  }

  // If the user is signed in and visits the root, send them to the dashboard
  if (req.auth && pathname === "/") {
    return NextResponse.redirect(new URL("/dashboard", req.url))
  }
})

export const config = {
  matcher: ["/", "/dashboard/:path*", "/profile/:path*"],
}
