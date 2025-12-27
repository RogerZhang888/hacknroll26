import { createClient } from "@/lib/supabase/client";

//if id is provided, get question with that id, otherwise, get a random question
export default async function GetCodeQuestion(id?: number) {
    const client = createClient();
    let query = client.from("code_questions").select("*");

    if (id !== undefined) {
        const { data, error} = await query.eq("id", id).single();
        if (error) {
            console.error(error);
        }
        return data;
    } else {
        const { data, error } = await query
            .order("random()")
            .limit(1)
            .single();
        if (error) {
            console.error(error);
        }
        return data;
    }
}
