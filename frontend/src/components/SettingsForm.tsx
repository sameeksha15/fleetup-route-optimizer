"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";

const toTime = (min: number) =>
  `${String(Math.floor(min / 60)).padStart(2, "0")}:${String(min % 60).padStart(2, "0")}`;
const toMinutes = (hhmm: string) => {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
};

export default function SettingsForm() {
  const [name, setName] = useState("");
  const [start, setStart] = useState("09:00");
  const [end, setEnd] = useState("18:00");
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .getOrgSettings()
      .then((s) => {
        setName(s.name);
        setStart(toTime(s.working_hours_start_min));
        setEnd(toTime(s.working_hours_end_min));
        setLoaded(true);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load settings"));
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      await api.updateOrgSettings({
        name: name.trim(),
        working_hours_start_min: toMinutes(start),
        working_hours_end_min: toMinutes(end),
      });
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Settings</h1>

      <Card className="max-w-lg">
        <CardHeader>
          <CardTitle className="text-base">Organization</CardTitle>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}
          <form onSubmit={submit} className="space-y-4">
            <div>
              <Label htmlFor="org-name">Company name</Label>
              <Input
                id="org-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                disabled={!loaded}
              />
            </div>
            <div>
              <Label>Working hours</Label>
              <p className="mb-1 text-xs text-muted-foreground">
                The default delivery window for orders that don&apos;t specify one.
              </p>
              <div className="grid grid-cols-2 gap-3">
                <Input
                  aria-label="Opening time"
                  type="time"
                  value={start}
                  onChange={(e) => setStart(e.target.value)}
                  disabled={!loaded}
                />
                <Input
                  aria-label="Closing time"
                  type="time"
                  value={end}
                  onChange={(e) => setEnd(e.target.value)}
                  disabled={!loaded}
                />
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Button type="submit" disabled={saving || !loaded || !name.trim()}>
                {saving ? "Saving…" : "Save changes"}
              </Button>
              {saved && <span className="text-sm text-emerald-600">Saved.</span>}
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
