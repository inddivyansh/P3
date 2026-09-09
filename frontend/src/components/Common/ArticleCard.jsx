export function ArticleCard({
  article,
  onRead,
}) {
  return (
    <div className="article-card">
      <div className="article-top">
        <span
          className={`category-tag ${article.categoryClass || "blue"}`}
        >
          {article.category}
        </span>
        {article.confidence !== undefined && (
          <div className="confidence">
            <span className="confidence-dot" />
            {article.confidence}%
          </div>
        )}
      </div>
      <h3>{article.title}</h3>
      <p className="article-summary">{article.summary}</p>
      <div className="article-footer">
        <div className="article-meta">
          <span>{article.source}</span>
          <span className="meta-separator">•</span>
          <span>{article.date}</span>
        </div>
        {onRead && (
          <button className="read-button" onClick={() => onRead(article)}>
            READ ARTICLE →
          </button>
        )}
      </div>
    </div>
  );
}
