"use client";

import { FileUp, Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

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

export function DocumentUploadForm() {
  const { error, saving, run } = useSubmit();
  const [documentType, setDocumentType] = useState("sales_request");
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState("");

  function toBase64(selected: File) {
    return new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || "").split(",")[1] || "");
      reader.onerror = () => reject(new Error("No se pudo leer archivo"));
      reader.readAsDataURL(selected);
    });
  }

  return (
    <form
      className="card max-w-2xl"
      onSubmit={(event) => {
        event.preventDefault();
        if (!file) return;
        run(async () => {
          const content_b64 = await toBase64(file);
          await postSkill("vertical_multi_shopper/document_skill", {
            action: "create",
            file_name: file.name,
            file_type: file.type || "application/octet-stream",
            document_type: documentType,
            content_b64,
          });
          setMessage("Documento guardado");
          setFile(null);
        });
      }}
    >
      <label className="label">Tipo</label>
      <select className="input mb-4" value={documentType} onChange={(event) => setDocumentType(event.target.value)}>
        <option value="sales_request">Solicitud venta</option>
        <option value="supplier_quote">Cotizacion proveedor</option>
        <option value="customer_quote">Cotizacion cliente</option>
        <option value="price_list">Lista de precios</option>
        <option value="image_note">Nota imagen</option>
        <option value="unknown">Desconocido</option>
      </select>
      <label className="label">Archivo</label>
      <input className="input mb-5" type="file" onChange={(event) => setFile(event.target.files?.[0] || null)} required />
      <button className="btn-primary inline-flex items-center gap-2" disabled={saving || !file}>
        <FileUp size={16} />
        Guardar documento
      </button>
      {message && <p className="mt-4 text-sm text-green-300">{message}</p>}
      {error && <p className="mt-4 text-sm text-red-300">{error}</p>}
    </form>
  );
}
