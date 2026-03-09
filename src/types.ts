export interface Article {
  source: string;
  sourceName: string;
  category: string;
  title: string;
  titleOriginal: string;
  description: string;
  descriptionOriginal: string;
  content: string;
  contentOriginal: string;
  link: string;
  pubDate: string;
  image: string;
}

export interface NewsData {
  articles: Article[];
  updated: string;
  sourceCount: number;
}

export type Category = 'all' | 'world' | 'business' | 'tech' | 'korea';
