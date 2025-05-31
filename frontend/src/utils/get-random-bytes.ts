import { randomBytes } from "ethers";

export function getRandomBytes32() {
    return "0x" + Buffer.from(randomBytes(32)).toString("hex");
  }