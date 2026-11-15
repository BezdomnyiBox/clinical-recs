import { cva, type VariantProps } from "class-variance-authority";
import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

const variants = cva(
  "inline-flex items-center justify-center rounded-xl text-[15px] font-medium tracking-tight transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-40",
  {
    variants: {
      variant: {
        default: "bg-accent text-black hover:bg-[#f5d400]",
        dark: "bg-black text-white hover:bg-neutral-800",
        outline: "border border-black/10 bg-white text-black hover:bg-neutral-100",
        ghost: "text-black hover:bg-black/5",
      },
      size: { default: "h-12 px-5", sm: "h-9 px-4 text-sm" },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

type Props = ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof variants>;

export function Button({ className, variant, size, ...props }: Props) {
  return <button className={cn(variants({ variant, size }), className)} {...props} />;
}
