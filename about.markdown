@import "{{ site.theme }}";

.repo-list {
  margin: 2em 0;
  
  .repo-item {
    padding: 1em;
    margin-bottom: 1em;
    border: 1px solid #e1e4e8;
    border-radius: 6px;
    
    h2 {
      margin: 0;
      font-size: 1.4em;
      
      a {
        color: #0366d6;
        text-decoration: none;
        
        &:hover {
          text-decoration: underline;
        }
      }
    }
    
    .repo-description {
      color: #586069;
      margin: 0.5em 0;
    }
    
    .repo-meta {
      margin: 0.5em 0 0;
      font-size: 0.9em;
      
      .language {
        margin-right: 1em;
      }
      
      .stars {
        color: #586069;
      }
    }
  }
}