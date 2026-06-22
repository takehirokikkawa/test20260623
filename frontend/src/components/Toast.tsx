"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
} from "react";

export type ToastType = "success" | "error" | "info";

interface Toast {
  id: number;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  showToast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextValue>({
  showToast: () => {},
});

export function useToast(): ToastContextValue {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const counterRef = useRef(0);

  const showToast = useCallback((message: string, type: ToastType = "info") => {
    const id = ++counterRef.current;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3500);
  }, []);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {/* Toast container */}
      <div
        aria-live="polite"
        className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`
              pointer-events-auto flex items-start gap-3 rounded-lg px-4 py-3 shadow-lg text-sm font-medium
              transition-all duration-300
              ${
                toast.type === "success"
                  ? "bg-emerald-600 text-white"
                  : toast.type === "error"
                  ? "bg-red-600 text-white"
                  : "bg-slate-800 text-white"
              }
            `}
          >
            <span className="flex-1">{toast.message}</span>
            <button
              onClick={() => dismiss(toast.id)}
              className="shrink-0 text-white/70 hover:text-white leading-none"
              aria-label="Dismiss notification"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
