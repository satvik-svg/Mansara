import './globals.css';
import type { ReactNode } from 'react';

import { AppShell } from '@/components/layout/AppShell';

export const metadata = {
  title: 'Room Design AI',
  description: 'Offline-first room design workflow with SceneScript v2'
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
