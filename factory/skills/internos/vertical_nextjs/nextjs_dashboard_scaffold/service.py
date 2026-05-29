from __future__ import annotations

import json
import re
from pathlib import Path


class NextjsDashboardScaffoldService:
    def ejecutar(self, context: dict) -> dict:
        plan = context.get("dashboard_plan") or context.get("plan") or {}
        project = plan.get("project", {})
        slug = context.get("slug") or project.get("slug") or self._slug(project.get("name", "dashboard"))
        out_dir = Path(context.get("output_dir") or f"generated/next_dashboards/{slug}")
        files = self._files(slug, project, plan)
        if context.get("save", True):
            for rel, content in files.items():
                path = out_dir / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
        return {"ok": True, "data": {"output_dir": str(out_dir), "files": sorted(files.keys()), "dashboard_plan": plan}}

    def _slug(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "dashboard"

    def _files(self, slug: str, project: dict, plan: dict) -> dict[str, str]:
        title = project.get("name", "Factory Dashboard")
        return {
            "package.json": json.dumps({
                "name": slug,
                "version": "0.1.0",
                "private": True,
                "scripts": {"dev": "next dev", "build": "next build", "start": "next start", "lint": "next lint"},
                "dependencies": {
                    "@supabase/supabase-js": "^2.45.0",
                    "lucide-react": "^0.468.0",
                    "next": "^14.2.0",
                    "react": "^18.3.1",
                    "react-dom": "^18.3.1",
                    "recharts": "^2.12.7"
                },
                "devDependencies": {"typescript": "^5.5.0", "@types/node": "^20.14.0", "@types/react": "^18.3.0", "tailwindcss": "^3.4.0", "postcss": "^8.4.0", "autoprefixer": "^10.4.0"}
            }, indent=2),
            "next.config.mjs": "const nextConfig = {};\nexport default nextConfig;\n",
            "tsconfig.json": json.dumps({"compilerOptions": {"target": "es5", "lib": ["dom", "dom.iterable", "esnext"], "allowJs": True, "skipLibCheck": True, "strict": True, "noEmit": True, "esModuleInterop": True, "module": "esnext", "moduleResolution": "bundler", "resolveJsonModule": True, "isolatedModules": True, "jsx": "preserve", "incremental": True, "paths": {"@/*": ["./*"]}}, "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx"], "exclude": ["node_modules"]}, indent=2),
            "postcss.config.js": "module.exports = { plugins: { tailwindcss: {}, autoprefixer: {} } };\n",
            "tailwind.config.ts": "import type { Config } from 'tailwindcss';\nconst config: Config = { content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}', './lib/**/*.{ts,tsx}'], theme: { extend: {} }, plugins: [] };\nexport default config;\n",
            "app/globals.css": "@tailwind base;\n@tailwind components;\n@tailwind utilities;\n\nbody { background: #f6f7f9; color: #111827; }\n",
            "app/layout.tsx": f"import './globals.css';\nimport type {{ Metadata }} from 'next';\n\nexport const metadata: Metadata = {{ title: '{title}', description: 'Factory3 client dashboard' }};\n\nexport default function RootLayout({{ children }}: {{ children: React.ReactNode }}) {{\n  return <html lang=\"es\"><body>{{children}}</body></html>;\n}}\n",
            "app/page.tsx": "import DashboardPage from './dashboard/page';\nexport default DashboardPage;\n",
            "app/dashboard/page.tsx": self._page(title),
            "dashboard_plan.json": json.dumps(plan, indent=2, ensure_ascii=False),
            ".env.example": "NEXT_PUBLIC_SUPABASE_URL=\nNEXT_PUBLIC_SUPABASE_ANON_KEY=\nNEXT_PUBLIC_FACTORY_API_URL=\n",
        }

    def _page(self, title: str) -> str:
        return f"""import {{ BarChart3, Download, Filter }} from 'lucide-react';

export default function DashboardPage() {{
  return (
    <main className="min-h-screen">
      <aside className="fixed inset-y-0 left-0 w-64 border-r border-slate-200 bg-white px-5 py-6">
        <div className="text-sm font-semibold uppercase tracking-wide text-slate-500">Factory3</div>
        <h1 className="mt-2 text-xl font-semibold text-slate-950">{title}</h1>
        <nav className="mt-8 space-y-2 text-sm text-slate-700">
          <div className="rounded-md bg-slate-100 px-3 py-2 font-medium">Overview</div>
          <div className="px-3 py-2">Gastos</div>
          <div className="px-3 py-2">Exportar</div>
        </nav>
      </aside>
      <section className="ml-64 px-8 py-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-500">Dashboard operativo</p>
            <h2 className="text-2xl font-semibold text-slate-950">Overview</h2>
          </div>
          <div className="flex gap-2">
            <button className="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"><Filter size={{16}} /> Filtros</button>
            <button className="inline-flex items-center gap-2 rounded-md bg-slate-950 px-3 py-2 text-sm text-white"><Download size={{16}} /> Exportar</button>
          </div>
        </div>
        <div className="mt-6 grid grid-cols-4 gap-4">
          {{['Gasto total', 'Movimientos', 'Promedio', 'Categoria top'].map((label) => (
            <div key={{label}} className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-sm text-slate-500">{{label}}</p>
              <p className="mt-2 text-2xl font-semibold">$0.00</p>
            </div>
          ))}}
        </div>
        <div className="mt-6 rounded-lg border border-slate-200 bg-white p-5">
          <div className="flex items-center gap-2 text-slate-700"><BarChart3 size={{18}} /> Graficas y tablas se generan con los siguientes skills.</div>
        </div>
      </section>
    </main>
  );
}}
"""

