"use client"

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import { usePortfolioStore } from '@/stores/portfolio-store'
import { PlusCircle, Briefcase } from 'lucide-react'

export function CreatePortfolioDialog() {
  const [open, setOpen] = useState(false)
  const [step, setStep] = useState(1)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    chains: [] as string[],
  })

  const { createPortfolio } = usePortfolioStore()

  const handleCreate = () => {
    createPortfolio({
      name: formData.name,
      description: formData.description,
      chains: formData.chains,
      assets: [],
      totalValue: 0,
    })
    setOpen(false)
    resetForm()
  }

  const resetForm = () => {
    setStep(1)
    setFormData({
      name: '',
      description: '',
      chains: [],
    })
  }

  const chains = [
    { id: 'ethereum', name: 'Ethereum', icon: '🔷' },
    { id: 'polygon', name: 'Polygon', icon: '🟣' },
    { id: 'arbitrum', name: 'Arbitrum', icon: '🔵' },
    { id: 'optimism', name: 'Optimism', icon: '🔴' },
    { id: 'avalanche', name: 'Avalanche', icon: '🔺' },
    { id: 'bsc', name: 'BSC', icon: '🟡' },
  ]

  const toggleChain = (chainId: string) => {
    setFormData((prev) => ({
      ...prev,
      chains: prev.chains.includes(chainId)
        ? prev.chains.filter((c) => c !== chainId)
        : [...prev.chains, chainId],
    }))
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="gap-2">
          <PlusCircle className="h-4 w-4" />
          Create Portfolio
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Briefcase className="h-5 w-5" />
            Create New Portfolio
          </DialogTitle>
          <DialogDescription>
            Set up your portfolio to track assets across multiple chains
          </DialogDescription>
        </DialogHeader>

        <div className="mb-4">
          <Progress value={step * 50} className="h-2" />
        </div>

        {step === 1 && (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Portfolio Name</Label>
              <Input
                id="name"
                placeholder="My DeFi Portfolio"
                value={formData.name}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, name: e.target.value }))
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description (Optional)</Label>
              <Input
                id="description"
                placeholder="Track my DeFi investments"
                value={formData.description}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    description: e.target.value,
                  }))
                }
              />
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Select Chains</Label>
              <p className="text-sm text-muted-foreground">
                Choose the blockchains you want to track
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {chains.map((chain) => (
                <button
                  key={chain.id}
                  onClick={() => toggleChain(chain.id)}
                  className={`
                    flex items-center gap-2 p-3 rounded-lg border-2 transition-colors
                    ${
                      formData.chains.includes(chain.id)
                        ? 'border-primary bg-primary/10'
                        : 'border-gray-200 hover:border-gray-300'
                    }
                  `}
                >
                  <span className="text-xl">{chain.icon}</span>
                  <span className="font-medium">{chain.name}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        <DialogFooter>
          {step === 1 ? (
            <>
              <Button
                variant="outline"
                onClick={() => {
                  setOpen(false)
                  resetForm()
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={() => setStep(2)}
                disabled={!formData.name}
              >
                Next
              </Button>
            </>
          ) : (
            <>
              <Button variant="outline" onClick={() => setStep(1)}>
                Back
              </Button>
              <Button
                onClick={handleCreate}
                disabled={formData.chains.length === 0}
              >
                Create Portfolio
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
} 