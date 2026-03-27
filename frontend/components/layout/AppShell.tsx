import Link from 'next/link';
import type { ReactNode } from 'react';

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="shell">
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">Room Design AI</div>
          <nav className="nav">
            <Link href="/">Upload</Link>
            <Link href="/scan">Scan</Link>
            <Link href="/correct">Correct</Link>
            <Link href="/design">Design</Link>
          </nav>
        </div>
      </header>
      <main className="main">{children}</main>
    </div>
  );
}
