import { describe, expect, it } from "vitest";

import { checkPicture, MAX_PICTURE_BYTES, NOT_A_PICTURE, PICTURE_TOO_LARGE } from "./bulletin-images";
import { keys } from "./keys";

function file(type: string, size: number): File {
  return new File([new Uint8Array(size)], "picture", { type });
}

describe("the cover picture before it is uploaded (printed bulletin PR 3b)", () => {
  it("takes a JPEG or PNG of at most 10 MB and says the server's words otherwise", () => {
    expect(checkPicture(file("image/jpeg", 1000))).toBeNull();
    expect(checkPicture(file("image/jpeg", 0))).toBe(NOT_A_PICTURE); // an iCloud photo not downloaded yet
    expect(checkPicture(file("image/png", MAX_PICTURE_BYTES))).toBeNull();
    expect(checkPicture(file("image/heic", 1000))).toBe(NOT_A_PICTURE);
    expect(checkPicture(file("", 1000))).toBe(NOT_A_PICTURE);
    expect(checkPicture(file("image/jpeg", MAX_PICTURE_BYTES + 1))).toBe(PICTURE_TOO_LARGE);
  });

  it("keeps a picture's bytes under the church's key", () => {
    expect(keys.bulletinImage("c1", "p1")).toEqual(["church", "c1", "bulletin-image", "p1"]);
    expect(keys.bulletinImage("c1", "p1").slice(0, 2)).toEqual(keys.church("c1"));
  });
});
