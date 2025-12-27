import GetCodeQuestion from "@/lib/handlers/code";
import GetMCQQuestion from "@/lib/handlers/mcq";
import { NextResponse } from "next/server";

export async function GET(req: Request) {
  const id = Number(new URL(req.url).searchParams.get("id")) || undefined;
  const data = await GetCodeQuestion(id);
  return NextResponse.json(data);
}
