---
name: Next.js 15 App Router Scaffolding
description: Instructions and standard architecture for scaffolding modern, production-grade Next.js 15 applications with TypeScript, Tailwind CSS, Lucide Icons, and dark-mode glassmorphic styling.
---

# Next.js 15 App Router Scaffolding Workflow

When asked to scaffold or build a Next.js application, follow these exact guidelines:

## 1. Project Initialization
- Check if `package.json` exists in the target directory using `list_directory`.
- If starting from scratch, execute:
  ```powershell
  npx -y create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm --yes
  ```
- Install Lucide icons and utilities:
  ```powershell
  npm install lucide-react clsx tailwind-merge
  ```

## 2. Directory Structure Conventions
Ensure following structure in `src/`:
- `src/app/layout.tsx`: Root layout with dark mode class by default (`dark bg-[#0a0d14] text-slate-100`).
- `src/app/page.tsx`: Landing or main dashboard view with glassmorphism cards and cyan/emerald accents.
- `src/components/`: Modular, reusable components (`Header.tsx`, `Sidebar.tsx`, `Card.tsx`, etc.).
- `src/lib/utils.ts`: Standard `cn` helper for className merging.

## 3. Design Standards
- Dark cyber aesthetic with glassmorphism (`backdrop-blur-md bg-slate-900/60 border border-slate-800/80`).
- Responsive layouts with sticky headers, mobile slide-out drawers, and micro-interactions.
- Zero placeholder text or placeholder images.

## 4. Verification Step
- After writing or updating files, always execute `verify_build` tool to ensure TypeScript compiles with zero errors before reporting completion.
