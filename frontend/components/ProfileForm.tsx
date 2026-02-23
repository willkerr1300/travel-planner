"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"

type LoyaltyProgram = {
  program: string
  number: string
}

type ProfileData = {
  passport_number?: string
  tsa_known_traveler?: string
  seat_preference?: string
  meal_preference?: string
  loyalty_numbers?: LoyaltyProgram[]
}

const SEAT_OPTIONS = ["No preference", "Window", "Aisle", "Middle"]
const MEAL_OPTIONS = ["No preference", "Vegetarian", "Vegan", "Kosher", "Halal", "Gluten-free"]

export function ProfileForm({ initialData }: { initialData: ProfileData | null }) {
  const router = useRouter()
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [form, setForm] = useState<ProfileData>({
    passport_number: initialData?.passport_number ?? "",
    tsa_known_traveler: initialData?.tsa_known_traveler ?? "",
    seat_preference: initialData?.seat_preference ?? "No preference",
    meal_preference: initialData?.meal_preference ?? "No preference",
    loyalty_numbers: initialData?.loyalty_numbers ?? [],
  })

  const [loyaltyEntry, setLoyaltyEntry] = useState({ program: "", number: "" })

  function addLoyalty() {
    if (!loyaltyEntry.program || !loyaltyEntry.number) return
    setForm((f) => ({
      ...f,
      loyalty_numbers: [...(f.loyalty_numbers ?? []), { ...loyaltyEntry }],
    }))
    setLoyaltyEntry({ program: "", number: "" })
  }

  function removeLoyalty(index: number) {
    setForm((f) => ({
      ...f,
      loyalty_numbers: f.loyalty_numbers?.filter((_, i) => i !== index),
    }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setSaved(false)

    try {
      const res = await fetch("/api/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail ?? "Failed to save profile")
      }

      setSaved(true)
      router.refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong")
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      {/* Travel Documents */}
      <section className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
        <h2 className="text-base font-semibold text-zinc-900 mb-4">Travel Documents</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field
            label="Passport Number"
            type="password"
            placeholder="••••••••"
            value={form.passport_number ?? ""}
            onChange={(v) => setForm((f) => ({ ...f, passport_number: v }))}
            hint="Stored encrypted"
          />
          <Field
            label="TSA / Known Traveler Number"
            type="password"
            placeholder="••••••••"
            value={form.tsa_known_traveler ?? ""}
            onChange={(v) => setForm((f) => ({ ...f, tsa_known_traveler: v }))}
            hint="Stored encrypted"
          />
        </div>
      </section>

      {/* Preferences */}
      <section className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
        <h2 className="text-base font-semibold text-zinc-900 mb-4">Preferences</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <SelectField
            label="Seat Preference"
            options={SEAT_OPTIONS}
            value={form.seat_preference ?? "No preference"}
            onChange={(v) => setForm((f) => ({ ...f, seat_preference: v }))}
          />
          <SelectField
            label="Meal Preference"
            options={MEAL_OPTIONS}
            value={form.meal_preference ?? "No preference"}
            onChange={(v) => setForm((f) => ({ ...f, meal_preference: v }))}
          />
        </div>
      </section>

      {/* Loyalty Programs */}
      <section className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
        <h2 className="text-base font-semibold text-zinc-900 mb-4">Loyalty Programs</h2>

        {(form.loyalty_numbers ?? []).length > 0 && (
          <ul className="mb-4 space-y-2">
            {form.loyalty_numbers!.map((lp, i) => (
              <li
                key={i}
                className="flex items-center justify-between rounded-lg bg-zinc-50 px-4 py-2 text-sm"
              >
                <span>
                  <span className="font-medium text-zinc-900">{lp.program}</span>
                  <span className="ml-2 text-zinc-500">{lp.number}</span>
                </span>
                <button
                  type="button"
                  onClick={() => removeLoyalty(i)}
                  className="text-xs text-red-500 hover:text-red-700 transition"
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}

        <div className="flex gap-2 items-end">
          <Field
            label="Airline / Hotel Program"
            placeholder="e.g. United MileagePlus"
            value={loyaltyEntry.program}
            onChange={(v) => setLoyaltyEntry((e) => ({ ...e, program: v }))}
          />
          <Field
            label="Member Number"
            placeholder="e.g. MP123456"
            value={loyaltyEntry.number}
            onChange={(v) => setLoyaltyEntry((e) => ({ ...e, number: v }))}
          />
          <button
            type="button"
            onClick={addLoyalty}
            className="mb-0.5 shrink-0 rounded-lg border border-zinc-300 px-4 py-2.5 text-sm font-medium text-zinc-700 hover:bg-zinc-50 transition"
          >
            Add
          </button>
        </div>
      </section>

      {/* Submit */}
      <div className="flex items-center gap-4">
        <button
          type="submit"
          disabled={saving}
          className="rounded-full bg-zinc-900 px-8 py-3 text-sm font-medium text-white shadow-sm transition hover:bg-zinc-700 disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save Profile"}
        </button>
        {saved && (
          <span className="text-sm text-green-600 font-medium">Saved!</span>
        )}
        {error && (
          <span className="text-sm text-red-600">{error}</span>
        )}
      </div>
    </form>
  )
}

function Field({
  label,
  type = "text",
  placeholder,
  value,
  onChange,
  hint,
}: {
  label: string
  type?: string
  placeholder?: string
  value: string
  onChange: (v: string) => void
  hint?: string
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-medium text-zinc-700">
        {label}
        {hint && <span className="ml-2 text-xs text-zinc-400 font-normal">{hint}</span>}
      </label>
      <input
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-zinc-200 px-3 py-2.5 text-sm text-zinc-900 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-900/20"
      />
    </div>
  )
}

function SelectField({
  label,
  options,
  value,
  onChange,
}: {
  label: string
  options: string[]
  value: string
  onChange: (v: string) => void
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-medium text-zinc-700">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-zinc-200 px-3 py-2.5 text-sm text-zinc-900 focus:outline-none focus:ring-2 focus:ring-zinc-900/20"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </div>
  )
}
