import { Header } from "@/components/layout/Header";
import { NewsStream } from "@/components/feed/NewsStream";
import { getArticles } from "@/lib/api";

export const revalidate = 0;

export default async function LiveFeedPage() {
  let initialArticles = [];
  try {
    initialArticles = await getArticles({ limit: 100 });
  } catch {
    // API may not be up in dev
  }

  return (
    <div className="flex flex-col h-screen">
      <Header
        title="Live Feed"
        subtitle="Real-time news stream from 1000+ sources"
      />
      <div className="flex-1 overflow-hidden p-6 flex flex-col">
        <NewsStream initialArticles={initialArticles} />
      </div>
    </div>
  );
}
