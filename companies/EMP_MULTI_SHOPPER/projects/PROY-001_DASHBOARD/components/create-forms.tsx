"use client";

import { FileUp, Loader2, Plus, Sparkles, PackagePlus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

async function postSkill(skill: string, body: Record<string, unknown>) {
  const res = await fetch("/api/multi-shopper", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ skill, ...body }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.ok === false) throw new Error(data.error || "No se pudo guardar");
  return data;
}

function useSubmit() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  async function run(fn: () => Promise<void>) {
    setSaving(true);
    setError("");
    try {
      await fn();
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setSaving(false);
    }
  }
  return { error, saving, run };
}

export function SalesQuoteCreateForm() {
  const { error, saving, run } = useSubmit();
  const [customerName, setCustomerName] = useState("");
  const [projectName, setProjectName] = useState("");
  return (
    <form
      className="card mb-5 grid grid-cols-1 gap-3 md:grid-cols-[1fr_1fr_auto]"
      onSubmit={(event) => {
        event.preventDefault();
        run(async () => {
          await postSkill("vertical_multi_shopper/sales_quote_skill", {
            action: "create",
            customer_name: customerName,
            project_name: projectName || undefined,
            status: "draft",
          });
          setCustomerName("");
          setProjectName("");
        });
      }}
    >
      <div>
        <label className="label">Cliente</label>
        <input className="input" value={customerName} onChange={(event) => setCustomerName(event.target.value)} required />
      </div>
      <div>
        <label className="label">Proyecto</label>
        <input className="input" value={projectName} onChange={(event) => setProjectName(event.target.value)} />
      </div>
      <div className="flex items-end">
        <button className="btn-primary inline-flex items-center gap-2" disabled={saving}>
          <Plus size={16} />
          Guardar
        </button>
      </div>
      {error && <p className="text-sm text-red-300 md:col-span-3">{error}</p>}
    </form>
  );
}

export function ProductCreateForm() {
  const { error, saving, run } = useSubmit();
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [unit, setUnit] = useState("pieza");
  return (
    <form
      className="card mb-5 grid grid-cols-1 gap-3 md:grid-cols-[1fr_180px_140px_auto]"
      onSubmit={(event) => {
        event.preventDefault();
        run(async () => {
          await postSkill("vertical_multi_shopper/products_skill", {
            action: "create",
            canonical_name: name,
            category_name: category || undefined,
            unit,
          });
          setName("");
          setCategory("");
          setUnit("pieza");
        });
      }}
    >
      <div>
        <label className="label">Producto</label>
        <input className="input" value={name} onChange={(event) => setName(event.target.value)} required />
      </div>
      <div>
        <label className="label">Categoria</label>
        <input className="input" value={category} onChange={(event) => setCategory(event.target.value)} />
      </div>
      <div>
        <label className="label">Unidad</label>
        <input className="input" value={unit} onChange={(event) => setUnit(event.target.value)} />
      </div>
      <div className="flex items-end">
        <button className="btn-primary inline-flex items-center gap-2" disabled={saving}>
          <Plus size={16} />
          Guardar
        </button>
      </div>
      {error && <p className="text-sm text-red-300 md:col-span-4">{error}</p>}
    </form>
  );
}

export function SupplierCreateForm() {
  const { error, saving, run } = useSubmit();
  const [name, setName] = useState("");
  const [city, setCity] = useState("");
  const [supplierType, setSupplierType] = useState("distributor");
  return (
    <form
      className="card mb-5 grid grid-cols-1 gap-3 md:grid-cols-[1fr_180px_180px_auto]"
      onSubmit={(event) => {
        event.preventDefault();
        run(async () => {
          await postSkill("vertical_multi_shopper/supplier_registry_skill", {
            action: "create",
            name,
            city: city || undefined,
            supplier_type: supplierType,
          });
          setName("");
          setCity("");
          setSupplierType("distributor");
        });
      }}
    >
      <div>
        <label className="label">Proveedor</label>
        <input className="input" value={name} onChange={(event) => setName(event.target.value)} required />
      </div>
      <div>
        <label className="label">Ciudad</label>
        <input className="input" value={city} onChange={(event) => setCity(event.target.value)} />
      </div>
      <div>
        <label className="label">Tipo</label>
        <select className="input" value={supplierType} onChange={(event) => setSupplierType(event.target.value)}>
          <option value="manufacturer">manufacturer</option>
          <option value="wholesaler">wholesaler</option>
          <option value="distributor">distributor</option>
          <option value="local_supplier">local_supplier</option>
          <option value="service_provider">service_provider</option>
          <option value="transport">transport</option>
        </select>
      </div>
      <div className="flex items-end">
        <button className="btn-primary inline-flex items-center gap-2" disabled={saving}>
          <Plus size={16} />
          Guardar
        </button>
      </div>
      {error && <p className="text-sm text-red-300 md:col-span-4">{error}</p>}
    </form>
  );
}

export function PurchaseQuoteCreateForm({
  suppliers,
  salesQuotes,
}: {
  suppliers: Array<{ id: string; name: string }>;
  salesQuotes: Array<{ id: string; folio?: string; customer_name: string }>;
}) {
  const { error, saving, run } = useSubmit();
  const [supplierId, setSupplierId] = useState("");
  const [salesQuoteId, setSalesQuoteId] = useState("");
  const [subject, setSubject] = useState("");
  return (
    <form
      className="card mb-5 grid grid-cols-1 gap-3 md:grid-cols-[1fr_1fr_1fr_auto]"
      onSubmit={(event) => {
        event.preventDefault();
        run(async () => {
          await postSkill("vertical_multi_shopper/purchase_quote_generator_skill", {
            action: "create",
            supplier_id: supplierId,
            sales_quote_id: salesQuoteId || undefined,
            subject: subject || "Solicitud de cotizacion",
          });
          setSubject("");
        });
      }}
    >
      <div>
        <label className="label">Proveedor</label>
        <select className="input" value={supplierId} onChange={(event) => setSupplierId(event.target.value)} required>
          <option value="">Seleccionar</option>
          {suppliers.map((supplier) => <option key={supplier.id} value={supplier.id}>{supplier.name}</option>)}
        </select>
      </div>
      <div>
        <label className="label">Cotizacion venta</label>
        <select className="input" value={salesQuoteId} onChange={(event) => setSalesQuoteId(event.target.value)}>
          <option value="">Sin ligar</option>
          {salesQuotes.map((quote) => <option key={quote.id} value={quote.id}>{quote.folio || quote.customer_name}</option>)}
        </select>
      </div>
      <div>
        <label className="label">Asunto</label>
        <input className="input" value={subject} onChange={(event) => setSubject(event.target.value)} />
      </div>
      <div className="flex items-end">
        <button className="btn-primary inline-flex items-center gap-2" disabled={saving || !supplierId}>
          <Plus size={16} />
          Generar
        </button>
      </div>
      {error && <p className="text-sm text-red-300 md:col-span-4">{error}</p>}
    </form>
  );
}

type ExtractedProduct = {
  raw_description: string | null;
  quantity: number | null;
  unit: string | null;
  unit_price: number | null;
  subtotal: number | null;
  brand: string | null;
  category_name: string | null;
};

type ExtractedData = {
  supplier_name: string | null;
  document_date: string | null;
  currency: string | null;
  products: ExtractedProduct[];
  summary: string | null;
};

export function DocumentUploadForm() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [documentType, setDocumentType] = useState("supplier_quote");
  const [file, setFile] = useState<File | null>(null);

  // Step 1 — upload
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [docId, setDocId] = useState<string | null>(null);
  const [canExtract, setCanExtract] = useState(false);

  // Step 2 — extract
  const [extracting, setExtracting] = useState(false);
  const [extractError, setExtractError] = useState("");
  const [extracted, setExtracted] = useState<ExtractedData | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());

  // Step 3 — import
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<{
    products_created: number;
    products_found: number;
    prices_created: number;
    errors: number;
    supplier: { name: string | null; folio: string | null; action: string | null };
  } | null>(null);
  const [importError, setImportError] = useState("");

  function toBase64(f: File) {
    return new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || "").split(",")[1] || "");
      reader.onerror = () => reject(new Error("No se pudo leer archivo"));
      reader.readAsDataURL(f);
    });
  }

  function reset() {
    setFile(null);
    setDocId(null);
    setCanExtract(false);
    setExtracted(null);
    setSelected(new Set());
    setImportResult(null);
    setUploadError("");
    setExtractError("");
    setImportError("");
    if (fileRef.current) fileRef.current.value = "";
  }

  async function handleUpload(event: React.FormEvent) {
    event.preventDefault();
    if (!file) return;
    setUploading(true);
    setUploadError("");
    try {
      const content_b64 = await toBase64(file);
      const data = await postSkill("vertical_multi_shopper/document_skill", {
        action: "create",
        file_name: file.name,
        file_type: file.type || "application/octet-stream",
        document_type: documentType,
        content_b64,
      });
      const doc = data?.data?.document;
      setDocId(doc?.id || null);
      setCanExtract(data?.data?.can_extract ?? false);
      router.refresh();
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Error al subir");
    } finally {
      setUploading(false);
    }
  }

  async function handleExtract() {
    if (!docId) return;
    setExtracting(true);
    setExtractError("");
    setExtracted(null);
    try {
      const data = await postSkill("vertical_multi_shopper/document_skill", {
        action: "extract",
        id: docId,
      });
      const ext: ExtractedData = data?.data?.extracted || { supplier_name: null, document_date: null, currency: null, products: [], summary: null };
      setExtracted(ext);
      setSelected(new Set(ext.products.map((_: ExtractedProduct, i: number) => i)));
    } catch (err) {
      setExtractError(err instanceof Error ? err.message : "Error al extraer");
    } finally {
      setExtracting(false);
    }
  }

  async function handleImport() {
    if (!extracted) return;
    setImporting(true);
    setImportError("");
    try {
      const toImport = extracted.products.filter((_, i) => selected.has(i));
      const data = await postSkill("vertical_multi_shopper/document_skill", {
        action: "import_products",
        products: toImport,
        document_id: docId,
        supplier_name: extracted.supplier_name,
        currency: extracted.currency,
        document_date: extracted.document_date,
        dry_run: false,
      });
      setImportResult({
        products_created: data?.data?.products_created ?? 0,
        products_found: data?.data?.products_found ?? 0,
        prices_created: data?.data?.prices_created ?? 0,
        errors: data?.data?.errors ?? 0,
        supplier: data?.data?.supplier ?? { name: null, folio: null, action: null },
      });
      router.refresh();
    } catch (err) {
      setImportError(err instanceof Error ? err.message : "Error al importar");
    } finally {
      setImporting(false);
    }
  }

  function toggleProduct(i: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  }

  // — Paso 3: resultado de importacion
  if (importResult) {
    const { supplier, products_created, products_found, prices_created, errors } = importResult;
    return (
      <div className="card max-w-2xl space-y-3">
        <p className="font-semibold text-green-300">Importacion completada</p>
        {supplier.name && (
          <p className="text-sm">
            <span className="text-muted">Proveedor: </span>
            <span className="font-medium">{supplier.name}</span>
            {supplier.folio && <span className="ml-2 font-mono text-xs text-slate-400">{supplier.folio}</span>}
            {supplier.action === "created" && <span className="ml-2 text-xs text-blue-300">(nuevo)</span>}
          </p>
        )}
        <div className="grid grid-cols-3 gap-3 text-center text-sm">
          <div className="rounded-lg bg-slate-800 p-3">
            <p className="text-xl font-bold text-white">{products_created}</p>
            <p className="text-xs text-muted">productos nuevos</p>
          </div>
          <div className="rounded-lg bg-slate-800 p-3">
            <p className="text-xl font-bold text-white">{products_found}</p>
            <p className="text-xs text-muted">ya existian</p>
          </div>
          <div className="rounded-lg bg-slate-800 p-3">
            <p className="text-xl font-bold text-green-400">{prices_created}</p>
            <p className="text-xs text-muted">precios guardados</p>
          </div>
        </div>
        {errors > 0 && <p className="text-sm text-yellow-300">{errors} item(s) con error</p>}
        <button className="btn-primary" onClick={reset}>Subir otro documento</button>
      </div>
    );
  }

  // — Paso 2: revisar productos extraidos
  if (extracted) {
    const prods = extracted.products || [];
    return (
      <div className="card max-w-2xl space-y-4">
        <div>
          <p className="text-sm font-semibold">Productos extraidos por IA</p>
          {extracted.supplier_name && <p className="text-sm text-muted">Proveedor: {extracted.supplier_name}</p>}
          {extracted.currency && <p className="text-sm text-muted">Moneda: {extracted.currency}</p>}
          {extracted.summary && <p className="mt-1 text-xs text-slate-400">{extracted.summary}</p>}
        </div>
        {prods.length === 0 ? (
          <p className="text-sm text-yellow-300">No se encontraron productos en el documento.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-sm">
              <thead className="table-head">
                <tr>
                  <th className="px-2 py-2 w-8">
                    <input type="checkbox" checked={selected.size === prods.length} onChange={() => setSelected(selected.size === prods.length ? new Set() : new Set(prods.map((_: ExtractedProduct, i: number) => i)))} />
                  </th>
                  <th className="px-2 py-2 text-left">Descripcion</th>
                  <th className="px-2 py-2">Cant</th>
                  <th className="px-2 py-2">Unidad</th>
                  <th className="px-2 py-2">Precio unit</th>
                  <th className="px-2 py-2">Marca</th>
                </tr>
              </thead>
              <tbody>
                {prods.map((p: ExtractedProduct, i: number) => (
                  <tr key={i} className={selected.has(i) ? "" : "opacity-40"}>
                    <td className="table-cell text-center"><input type="checkbox" checked={selected.has(i)} onChange={() => toggleProduct(i)} /></td>
                    <td className="table-cell">{p.raw_description || "-"}</td>
                    <td className="table-cell text-center">{p.quantity ?? "-"}</td>
                    <td className="table-cell text-center">{p.unit || "-"}</td>
                    <td className="table-cell text-right">{p.unit_price != null ? `$${p.unit_price}` : "-"}</td>
                    <td className="table-cell">{p.brand || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {importError && <p className="text-sm text-red-300">{importError}</p>}
        <div className="flex gap-3">
          {prods.length > 0 && (
            <button
              className="btn-primary inline-flex items-center gap-2"
              disabled={importing || selected.size === 0}
              onClick={handleImport}
            >
              {importing ? <Loader2 size={15} className="animate-spin" /> : <PackagePlus size={15} />}
              Importar {selected.size} producto(s)
            </button>
          )}
          <button className="btn-ghost" onClick={reset}>Cancelar</button>
        </div>
      </div>
    );
  }

  // — Paso 1a: documento subido, mostrar opcion de extraccion
  if (docId) {
    return (
      <div className="card max-w-2xl space-y-4">
        <p className="text-sm text-green-300 font-semibold">Documento guardado correctamente.</p>
        {canExtract ? (
          <>
            <p className="text-sm text-muted">Puedes extraer los productos listados en el documento con IA.</p>
            {extractError && <p className="text-sm text-red-300">{extractError}</p>}
            <div className="flex gap-3">
              <button
                className="btn-primary inline-flex items-center gap-2"
                disabled={extracting}
                onClick={handleExtract}
              >
                {extracting ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />}
                {extracting ? "Extrayendo..." : "Extraer productos con IA"}
              </button>
              <button className="btn-ghost" onClick={reset}>Subir otro</button>
            </div>
          </>
        ) : (
          <div className="flex gap-3">
            <p className="text-sm text-muted">El tipo de archivo no soporta extraccion automatica.</p>
            <button className="btn-ghost" onClick={reset}>Subir otro</button>
          </div>
        )}
      </div>
    );
  }

  // — Paso 0: formulario de subida
  return (
    <form className="card max-w-2xl" onSubmit={handleUpload}>
      <label className="label">Tipo de documento</label>
      <select className="input mb-4" value={documentType} onChange={(e) => setDocumentType(e.target.value)}>
        <option value="supplier_quote">Cotizacion proveedor</option>
        <option value="sales_request">Solicitud venta</option>
        <option value="customer_quote">Cotizacion cliente</option>
        <option value="price_list">Lista de precios</option>
        <option value="image_note">Nota imagen</option>
        <option value="unknown">Desconocido</option>
      </select>
      <label className="label">Archivo (xlsx, pdf, imagen)</label>
      <input
        ref={fileRef}
        className="input mb-5"
        type="file"
        accept=".xlsx,.xls,.pdf,.png,.jpg,.jpeg,.webp"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
        required
      />
      <button className="btn-primary inline-flex items-center gap-2" disabled={uploading || !file}>
        {uploading ? <Loader2 size={16} className="animate-spin" /> : <FileUp size={16} />}
        {uploading ? "Subiendo..." : "Subir documento"}
      </button>
      {uploadError && <p className="mt-4 text-sm text-red-300">{uploadError}</p>}
    </form>
  );
}
