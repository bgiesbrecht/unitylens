import { Search } from 'lucide-react';
import { useState } from 'react';
import { useRouter } from '../router';

interface SearchBarProps {
  compact?: boolean;
  placeholder?: string;
}

export function SearchBar({ compact, placeholder }: SearchBarProps) {
  const { navigate } = useRouter();
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      navigate(`/search?q=${encodeURIComponent(query.trim())}`);
    }
  };

  if (compact) {
    return (
      <form onSubmit={handleSubmit} className="header-search">
        <div className="header-search-wrapper">
          <Search className="header-search-icon" />
          <input
            type="text"
            className="header-search-input"
            placeholder={placeholder || 'Search catalog...'}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      </form>
    );
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="search-input-large-wrapper">
        <Search className="search-input-large-icon" />
        <input
          type="text"
          className="search-input-large"
          placeholder={placeholder || 'Ask a question about your data catalog...'}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button type="submit" className="search-input-large-btn">
          <Search size={16} />
        </button>
      </div>
    </form>
  );
}
