import { DocumentUploadForm } from "@/components/create-forms";
import PageHeader from "@/components/page-header";

export default function AddDocumentPage() {
  return (
    <div>
      <PageHeader title="Subir documento" subtitle="xlsx, PDF o imagen — extrae productos con IA" />
      <DocumentUploadForm />
    </div>
  );
}
