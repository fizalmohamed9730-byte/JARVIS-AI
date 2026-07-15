import clsx from 'clsx';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export default function LoadingSpinner({ size = 'md', className }: LoadingSpinnerProps) {
  const sizes = { sm: 'h-4 w-4', md: 'h-8 w-8', lg: 'h-12 w-12' };

  return (
    <div className={clsx('flex items-center justify-center', className)}>
      <div className="relative">
        <div className={clsx('animate-spin rounded-full border-2 border-blue-500/20 border-t-blue-500', sizes[size])} />
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-[8px] font-bold text-blue-400">J</span>
        </div>
      </div>
    </div>
  );
}
