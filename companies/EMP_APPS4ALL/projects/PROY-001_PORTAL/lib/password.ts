import { verify } from "@node-rs/argon2";

export async function verifyPassword(password: string, passwordHash: string) {
  return verify(passwordHash, password);
}
