import { describe, expect, it } from "vitest";

import { checkPicture, isLatestChoice, MAX_PICTURE_BYTES, newChoice, NOT_A_PICTURE, PICTURE_TOO_LARGE, uploadKey } from "./bulletin-images";
import { keys } from "./keys";

function file(type: string, size: number, name = "picture"): File {
  return new File([new Uint8Array(size)], name, { type });
}

describe("the cover picture before it is uploaded (printed bulletin PR 3b)", () => {
  it("takes a JPEG or PNG of at most 10 MB and says the server's words otherwise", () => {
    expect(checkPicture(file("image/jpeg", 1000))).toBeNull();
    expect(checkPicture(file("image/jpeg", 0))).toBe(NOT_A_PICTURE); // an iCloud photo not downloaded yet
    expect(checkPicture(file("image/png", MAX_PICTURE_BYTES))).toBeNull();
    expect(checkPicture(file("image/heic", 1000))).toBe(NOT_A_PICTURE);
    expect(checkPicture(file("", 1000))).toBe(NOT_A_PICTURE); // no type and no picture name
    expect(checkPicture(file("image/jpeg", MAX_PICTURE_BYTES + 1))).toBe(PICTURE_TOO_LARGE);
  });

  it("goes by the name when a phone gives a blank or loose type, and still refuses another kind (PR 3b build review M7)", () => {
    expect(checkPicture(file("", 1000, "IMG_0001.JPG"))).toBeNull();
    expect(checkPicture(file("", 1000, "scan.jpeg"))).toBeNull();
    expect(checkPicture(file("", 1000, "drawing.png"))).toBeNull();
    expect(checkPicture(file("image/jpg", 1000, "photo.jpg"))).toBeNull();
    expect(checkPicture(file("image/pjpeg", 1000, "photo.jpg"))).toBeNull();
    expect(checkPicture(file("", 1000, "photo.heic"))).toBe(NOT_A_PICTURE);
    expect(checkPicture(file("image/heic", 1000, "photo.jpg"))).toBe(NOT_A_PICTURE);
    expect(checkPicture(file("image/gif", 1000, "card.png"))).toBe(NOT_A_PICTURE);
    expect(checkPicture(file("", 0, "photo.jpg"))).toBe(NOT_A_PICTURE);
    expect(checkPicture(file("", MAX_PICTURE_BYTES + 1, "photo.jpg"))).toBe(PICTURE_TOO_LARGE);
  });

  it("keeps a picture's bytes under the church's key", () => {
    expect(keys.bulletinImage("c1", "p1")).toEqual(["church", "c1", "bulletin-image", "p1"]);
    expect(keys.bulletinImage("c1", "p1").slice(0, 2)).toEqual(keys.church("c1"));
  });

  it("keeps the latest choice per draft, so only its upload applies, and one key per church for the uploads (PR 3b build review I1)", () => {
    const a = newChoice("c1:draft-x");
    const other = newChoice("c1:draft-y");
    expect(isLatestChoice("c1:draft-x", a)).toBe(true);
    const b = newChoice("c1:draft-x"); // a later Choose, or Remove
    expect(isLatestChoice("c1:draft-x", a)).toBe(false);
    expect(isLatestChoice("c1:draft-x", b)).toBe(true);
    expect(isLatestChoice("c1:draft-y", other)).toBe(true); // another draft's choice stands
    expect(uploadKey("c1")).toEqual(["bulletinImageUpload", "c1"]);
  });
});
