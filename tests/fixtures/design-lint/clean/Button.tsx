export function Button({ children }: { children: React.ReactNode }) {
  return (
    <button className="rounded-lg bg-[#2f5bea] px-4 py-2 text-white transition-transform duration-200 hover:-translate-y-px focus-visible:outline-2">
      {children}
    </button>
  );
}
export function IconButton() {
  return (
    <button aria-label="Close" className="size-8 p-1 rounded-md">
      <X />
    </button>
  );
}
