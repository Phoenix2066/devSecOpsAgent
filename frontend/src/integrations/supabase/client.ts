// Safe dummy Supabase client
export const supabase = new Proxy({} as any, {
  get: () => () => ({ data: { session: null }, error: null }),
});
