import { DocumentUploadForm } from "@/components/create-forms";
import PageHeader from "@/components/page-header";

export default function AddDocumentPage() {
  return (
    <div>
      <PageHeader title="Add documentos" subtitle="PDF, Excel, Word, imagen o texto" />
      <DocumentUploadForm />
    </div>
  );
}
