import { Icon, Link } from '@chakra-ui/react';
import { ExternalLink } from 'lucide-react';

// Enlace que abre en otra pestaña (portal de la DNCP, API). label es el texto
// completo para lectores de pantalla y al pasar el mouse.
export default function EnlaceExterno({ href, label, children }) {
  return (
    <Link
      href={href}
      target='_blank'
      rel='noopener noreferrer'
      colorPalette='blue'
      variant='underline'
      display='inline-flex'
      alignItems='center'
      gap={1}
      fontSize='sm'
      aria-label={label}
      title={label}
    >
      {children}
      <Icon asChild boxSize={3.5}>
        <ExternalLink />
      </Icon>
    </Link>
  );
}
