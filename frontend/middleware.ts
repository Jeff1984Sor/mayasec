export { default } from "next-auth/middleware";

export const config = {
  // Protege tudo exceto login, api/auth, estáticos
  matcher: ["/((?!login|api/auth|_next/static|_next/image|favicon.ico).*)"],
};
