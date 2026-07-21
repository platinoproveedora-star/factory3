import { ArrowLeft } from "lucide-react";
import { LogisticsDashboard } from "@/components/LogisticsDashboard";
import { reviewData } from "@/lib/review-data";

export default function ReviewPage() {
  return (
    <main className="min-h-screen bg-paper">
      <header className="sticky top-0 z-30 border-b border-line bg-white">
        <div className="mx-auto flex max-w-7xl items-center gap-3 px-3 py-3 sm:px-5">
          <a href="/" className="btn-soft min-h-10 px-3" title="Regresar">
            <ArrowLeft size={17} />
          </a>
          <div className="min-w-0 flex-1">
            <p className="text-lg font-semibold leading-tight text-ink">Logistics4All</p>
            <p className="truncate text-xs text-slate-500">Modo revision visual</p>
          </div>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold uppercase text-slate-600">Demo</span>
        </div>
      </header>
      <LogisticsDashboard initialData={reviewData} initialError="" companyId="EMP_REVIEW" companyName="Duralon Demo" reviewMode />
    </main>
  );
}
