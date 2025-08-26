import { useState, useEffect } from 'react';
import { api } from './api';
import { Card, Button } from './components';
import { ExternalLink } from 'lucide-react';

export default function CoursesPage() {
  const [courses, setCourses] = useState([]);

  useEffect(() => {
    // Carregar o arquivo JSON com os links dos cursos
    api('/courses')
      .then(data => setCourses(data.courses))
      .catch(error => console.error('Erro ao carregar os cursos:', error));
  }, []);

  return (
    <div style={{ padding: '24px' }}>
      <h2 style={{ marginBottom: '24px' }}>Links dos Cursos</h2>
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', 
        gap: '24px 24px' 
      }}>
        {courses.map((course) => (
          <Card 
            key={course.name}
            title={course.name}
          >
            <div style={{ 
              display: 'flex', 
              justifyContent: 'center', 
              marginTop: '16px' 
            }}>
              <Button
                onClick={() => window.open(course.url, '_blank', 'noopener,noreferrer')}
                style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
              >
                Acessar curso <ExternalLink size={16} />
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
