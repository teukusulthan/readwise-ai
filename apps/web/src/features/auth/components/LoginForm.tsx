import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { useLogin } from '@/features/auth/hooks/useLogin'
import { loginSchema, type TLoginFormValues } from '@/features/auth/schemas/login.schema'
import { REGISTER_PATH, safeNextPath } from '@/utils/auth-redirect'

/** Email (or username) + password. On success goes to `?next=` (a path inside the app) or the catalog. */
export function LoginForm() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const login = useLogin()
  const form = useForm<TLoginFormValues>({ resolver: zodResolver(loginSchema), defaultValues: { email: '', password: '' } })
  const next = params.get('next')

  const onSubmit = (values: TLoginFormValues) => {
    login.mutate(
      { email: values.email.trim(), password: values.password },
      {
        onSuccess: () => navigate(safeNextPath(next), { replace: true }),
        // Do not leave a rejected password sitting in the field.
        onError: () => form.resetField('password'),
      },
    )
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
        {params.get('registered') && (
          <p role="status" className="rounded-xl bg-primary-light px-4 py-3 text-body-sm text-primary-bold">
            Your account is ready. Sign in to continue.
          </p>
        )}
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email or username</FormLabel>
              <FormControl>
                <Input autoComplete="username" autoFocus {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Password</FormLabel>
              <FormControl>
                <Input type="password" autoComplete="current-password" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {login.error && (
          <p role="alert" className="text-body-sm text-error-bold">
            {login.error.message}
          </p>
        )}
        <Button type="submit" disabled={login.isPending}>
          {login.isPending ? 'Signing in…' : 'Sign in'}
        </Button>
        <p className="text-center text-body-sm text-font-secondary">
          No account yet?{' '}
          <Link to={REGISTER_PATH} className="font-semibold text-primary underline-offset-4 hover:underline">
            Create one
          </Link>
        </p>
      </form>
    </Form>
  )
}
