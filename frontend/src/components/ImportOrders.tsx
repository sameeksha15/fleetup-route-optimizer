"use client";

import { useState } from "react";
import { AlertCircle, CheckCircle2, FileUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api, type ImportPreview } from "@/lib/api";

export default function ImportOrders({
  onDone,
  onCancel,
}: {
  onDone: () => void;
  onCancel: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runPreview = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      setPreview(await api.importPreview(file));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not read the file");
    } finally {
      setBusy(false);
    }
  };

  const commit = async () => {
    if (!preview) return;
    const okOrders = preview.rows.filter((r) => r.status === "ok").map((r) => r.order);
    if (okOrders.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      await api.importCommit(okOrders);
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/50 p-4">
      <div className="flex max-h-[92vh] w-full max-w-2xl flex-col rounded-lg bg-white p-6">
        <h2 className="text-xl font-semibold">Import orders</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Upload your own CSV or Excel file. Columns are matched flexibly; addresses without
          coordinates are located automatically. Download a{" "}
          <a
            className="font-medium text-blue-600 hover:underline"
            href={api.importTemplateUrl("csv")}
          >
            CSV
          </a>{" "}
          or{" "}
          <a
            className="font-medium text-blue-600 hover:underline"
            href={api.importTemplateUrl("xlsx")}
          >
            Excel
          </a>{" "}
          template to see the expected columns.
        </p>

        {error && (
          <div className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        {!preview ? (
          <div className="mt-5 space-y-4">
            <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-gray-300 py-10 text-sm text-muted-foreground hover:border-gray-400">
              <FileUp className="h-6 w-6" />
              {file ? file.name : "Choose a .csv or .xlsx file"}
              <input
                type="file"
                accept=".csv,.xlsx,.xlsm"
                className="hidden"
                onChange={(e) => {
                  setFile(e.target.files?.[0] ?? null);
                  setPreview(null);
                }}
              />
            </label>
            <div className="flex justify-end gap-3">
              <Button variant="outline" onClick={onCancel}>
                Cancel
              </Button>
              <Button onClick={runPreview} disabled={!file || busy}>
                {busy ? "Reading…" : "Upload & preview"}
              </Button>
            </div>
          </div>
        ) : (
          <div className="mt-5 flex min-h-0 flex-1 flex-col">
            <div className="flex flex-wrap items-center gap-4 text-sm">
              <span className="flex items-center gap-1.5 text-emerald-700">
                <CheckCircle2 className="h-4 w-4" /> {preview.summary.ok} ready
              </span>
              <span className="flex items-center gap-1.5 text-red-700">
                <AlertCircle className="h-4 w-4" /> {preview.summary.errors} with problems
              </span>
              {preview.summary.geocoded > 0 && (
                <span className="text-muted-foreground">
                  {preview.summary.geocoded} address(es) located
                </span>
              )}
            </div>

            <div className="mt-3 min-h-0 flex-1 overflow-auto rounded-md border">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-gray-50">
                  <tr className="text-left text-muted-foreground">
                    <th className="px-3 py-2 font-medium">Row</th>
                    <th className="px-3 py-2 font-medium">Reference</th>
                    <th className="px-3 py-2 font-medium">Address</th>
                    <th className="px-3 py-2 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.rows.map((r) => (
                    <tr key={r.row} className="border-t align-top">
                      <td className="px-3 py-2 text-muted-foreground">{r.row}</td>
                      <td className="px-3 py-2">{r.order.reference ?? "—"}</td>
                      <td className="max-w-[240px] truncate px-3 py-2" title={r.order.address}>
                        {r.order.address}
                        {r.note === "geocoded" && (
                          <span className="ml-1 text-xs text-blue-600">(located)</span>
                        )}
                      </td>
                      <td className="px-3 py-2">
                        {r.status === "ok" ? (
                          <span className="text-emerald-700">Ready</span>
                        ) : (
                          <span className="text-red-600">{r.errors.join(" ")}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-4 flex justify-end gap-3">
              <Button
                variant="outline"
                onClick={() => {
                  setPreview(null);
                  setError(null);
                }}
              >
                Back
              </Button>
              <Button onClick={commit} disabled={busy || preview.summary.ok === 0}>
                {busy ? "Importing…" : `Import ${preview.summary.ok} valid order(s)`}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
