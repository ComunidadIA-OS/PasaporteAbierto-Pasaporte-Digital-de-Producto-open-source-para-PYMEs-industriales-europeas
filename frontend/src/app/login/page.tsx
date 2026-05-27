import { Suspense } from "react";

import { LoginPage } from "@/modules/auth/pages/LoginPage";

// `useSearchParams` (lee `?next=`) exige un límite de Suspense en App Router.
export default function Page() {
  return (
    <Suspense fallback={null}>
      <LoginPage />
    </Suspense>
  );
}
