import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

interface CreateProjectModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateProjectModal({ open, onOpenChange }: CreateProjectModalProps) {
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    repoLink: "",
    appId: "",
    userId: "",
    privateKey: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    // Validate fields
    if (!formData.repoLink || !formData.appId || !formData.userId || !formData.privateKey) {
      toast.error("Please fill in all fields");
      setLoading(false);
      return;
    }

    try {
      // Logic for creating project would go here
      console.log("Creating project with data:", formData);
      
      // Mock API call
      await new Promise((resolve) => setTimeout(resolve, 1000));

      toast.success("Project workflow replicated successfully!");
      onOpenChange(false);
      // Reset form
      setFormData({
        repoLink: "",
        appId: "",
        userId: "",
        privateKey: "",
      });
    } catch (error) {
      toast.error("Failed to create project");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px] bg-card border-border">
        <DialogHeader>
          <DialogTitle className="text-foreground">Replicate Workflow</DialogTitle>
          <DialogDescription className="text-muted-foreground">
            Configure a new GitHub project to enable autonomous self-healing.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="repo" className="text-muted-foreground uppercase text-[10px] tracking-wider">
              GitHub Repo Link
            </Label>
            <Input
              id="repo"
              placeholder="https://github.com/owner/repo"
              value={formData.repoLink}
              onChange={(e) => setFormData({ ...formData, repoLink: e.target.value })}
              className="bg-background border-border"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="appId" className="text-muted-foreground uppercase text-[10px] tracking-wider">
                GitHub App ID
              </Label>
              <Input
                id="appId"
                placeholder="123456"
                value={formData.appId}
                onChange={(e) => setFormData({ ...formData, appId: e.target.value })}
                className="bg-background border-border"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="userId" className="text-muted-foreground uppercase text-[10px] tracking-wider">
                GitHub User ID
              </Label>
              <Input
                id="userId"
                placeholder="owner-name"
                value={formData.userId}
                onChange={(e) => setFormData({ ...formData, userId: e.target.value })}
                className="bg-background border-border"
              />
            </div>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="privateKey" className="text-muted-foreground uppercase text-[10px] tracking-wider">
              GitHub Private Key
            </Label>
            <Textarea
              id="privateKey"
              placeholder="-----BEGIN RSA PRIVATE KEY-----..."
              className="min-h-[120px] font-mono text-[12px] bg-background border-border"
              value={formData.privateKey}
              onChange={(e) => setFormData({ ...formData, privateKey: e.target.value })}
            />
          </div>
          <DialogFooter className="pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              className="border-border hover:bg-muted"
            >
              Cancel
            </Button>
            <Button type="submit" disabled={loading} className="bg-primary text-primary-foreground hover:opacity-90">
              {loading ? "Replicating..." : "Start Replication"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
