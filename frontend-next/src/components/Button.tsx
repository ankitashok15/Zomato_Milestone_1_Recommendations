import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "inverted" | "outlined";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
};

const variantClass: Record<Variant, string> = {
  primary: "btn-primary",
  secondary: "btn-secondary",
  inverted: "btn-inverted",
  outlined: "btn-outlined",
};

export function Button({ variant = "primary", className = "", type = "button", ...props }: Props) {
  return <button type={type} className={`btn ${variantClass[variant]} ${className}`.trim()} {...props} />;
}
