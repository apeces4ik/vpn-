
import { Shield } from "lucide-react";

export function Logo() {
  return (
    <div className="flex items-center gap-2">
      <Shield className="w-8 h-8 text-primary animate-pulse" />
      <span className="font-bold text-xl tracking-tight">Security</span>
    </div>
  );
}
