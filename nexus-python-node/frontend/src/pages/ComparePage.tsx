import { useSearchParams } from 'react-router-dom';
import CompareAnalytics from '@/components/compare/compare-analytics';

export default function ComparePage() {
  const [searchParams] = useSearchParams();
  const symbol = searchParams.get('symbol') || undefined;
  return <CompareAnalytics initialSymbol={symbol} />;
}
