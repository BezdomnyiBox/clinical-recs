import { cva, type VariantProps } from "class-variance-authority";
import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

const variants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-primary disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:opacity-90",
        outline: "border bg-background hover:bg-muted",
        ghost: "hover:bg-muted",
      },
      size: { default: "h-9 px-4", sm: "h-8 px-3" },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

type Props = ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof variants>;

export function Button({ className, variant, size, ...props }: Props) {
  return <button className={cn(variants({ variant, size }), className)} {...props} />;
}
