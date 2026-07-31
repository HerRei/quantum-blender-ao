package ch.unibas.qmr.client;

import ch.unibas.qmr.scene.VoxelMaterial;
import ch.unibas.qmr.scene.VoxelSampler;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

/** Maps Minecraft block state into the deliberately small v1 material model. */
public final class MinecraftVoxelSampler implements VoxelSampler {
    private final Level level;

    public MinecraftVoxelSampler(Level level) {
        this.level = level;
    }

    @Override
    public VoxelMaterial sample(int worldX, int worldY, int worldZ) {
        BlockState state = level.getBlockState(new BlockPos(worldX, worldY, worldZ));
        boolean occupied = !state.isAir();
        boolean transparent = occupied && !state.canOcclude();
        return new VoxelMaterial(occupied, transparent, state.getLightEmission());
    }
}

