import { createClient } from "@/lib/supabase/client";

export default async function ApplyPage() {
    const { data, error } = await createClient()
    .from("code_questions")
    .select("*")
    .eq("type", "drill");

    if (error) {
        console.error(error);
        return <div>Error loading questions. </div>
    }
    
    return (
        //whatever you want to return

    );
}

