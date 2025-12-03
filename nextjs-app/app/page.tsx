"use client";

import { useSession, signIn, signOut } from "next-auth/react";
import Image from "next/image";

export default function Home() {
  const { data: session } = useSession();

  if (!session) {
    return (
      <div className="flex flex-col gap-3">
        <p>You are not logged in.</p>
        <button onClick={() => signIn("github")}>Log in with GitHub</button>
        <button onClick={() => signIn("google")}>Log in with Google</button>
      </div>
    );
  }

  return (
    <div>
      <pre>{JSON.stringify(session, null, 2)}</pre>
      <p>Logged in as {session.user?.name}</p>
      <p>Email: {session.user?.email}</p>
      <Image
        src={session.user?.image ?? ""}
        alt="avatar"
        style={{ width: 64, borderRadius: "50%" }}
        width={50}
        height={50}
      />
      <button onClick={() => signOut()}>Log out</button>
    </div>
  );
}
