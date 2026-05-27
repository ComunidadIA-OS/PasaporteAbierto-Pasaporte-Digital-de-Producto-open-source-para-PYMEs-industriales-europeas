import { WizardPage } from "@/modules/wizard/pages/WizardPage";

export default async function Page({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return <WizardPage sessionId={sessionId} />;
}
