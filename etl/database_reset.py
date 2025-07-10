"""
Complete Database Wipe
Removes all nodes, relationships, constraints, and indexes from Neo4j database.
Use this for a complete fresh start.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env file  
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Fallback: manually load .env file
    import os
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

from api.config import Settings, get_driver


async def drop_all_constraints(session):
    """Drop all constraints in the database."""
    print("🗑️  Dropping all constraints...")
    
    # Get all constraints
    result = await session.run("SHOW CONSTRAINTS")
    constraints = await result.data()
    
    for constraint in constraints:
        constraint_name = constraint.get('name')
        if constraint_name:
            try:
                await session.run(f"DROP CONSTRAINT {constraint_name}")
                print(f"   ✅ Dropped constraint: {constraint_name}")
            except Exception as e:
                print(f"   ⚠️  Could not drop constraint {constraint_name}: {e}")
    
    print(f"🗑️  Dropped {len(constraints)} constraints")


async def drop_all_indexes(session):
    """Drop all indexes in the database."""
    print("🗑️  Dropping all indexes...")
    
    # Get all indexes
    result = await session.run("SHOW INDEXES")
    indexes = await result.data()
    
    for index in indexes:
        index_name = index.get('name')
        if index_name:
            try:
                await session.run(f"DROP INDEX {index_name}")
                print(f"   ✅ Dropped index: {index_name}")
            except Exception as e:
                print(f"   ⚠️  Could not drop index {index_name}: {e}")
    
    print(f"🗑️  Dropped {len(indexes)} indexes")


async def delete_all_data(session):
    """Delete all nodes and relationships."""
    print("🗑️  Deleting all data...")
    
    # Count before deletion
    result = await session.run("MATCH (n) RETURN count(n) as node_count")
    data = await result.data()
    node_count = data[0]['node_count']
    
    result = await session.run("MATCH ()-[r]->() RETURN count(r) as rel_count")
    data = await result.data()
    rel_count = data[0]['rel_count']
    
    print(f"   📊 Before: {node_count} nodes, {rel_count} relationships")
    
    # Delete all relationships first
    await session.run("MATCH ()-[r]->() DELETE r")
    
    # Delete all nodes
    await session.run("MATCH (n) DELETE n")
    
    # Verify deletion
    result = await session.run("MATCH (n) RETURN count(n) as node_count")
    data = await result.data()
    remaining_nodes = data[0]['node_count']
    
    result = await session.run("MATCH ()-[r]->() RETURN count(r) as rel_count")
    data = await result.data()
    remaining_rels = data[0]['rel_count']
    
    print(f"   📊 After: {remaining_nodes} nodes, {remaining_rels} relationships")
    
    if remaining_nodes == 0 and remaining_rels == 0:
        print("   ✅ All data successfully deleted")
    else:
        print(f"   ⚠️  {remaining_nodes} nodes and {remaining_rels} relationships remain")


async def wipe_database():
    """Main function to completely wipe the database."""
    
    print("🧹 COMPLETE DATABASE WIPE")
    print("=========================")
    print("⚠️  WARNING: This will delete EVERYTHING in the database!")
    print("   - All nodes and relationships")
    print("   - All constraints and indexes")
    print("   - All data will be permanently lost")
    print()
    
    # Check for --force flag
    import sys
    if "--force" in sys.argv:
        print("🚀 --force flag detected, skipping confirmation")
    else:
        # Ask for confirmation
        try:
            confirmation = input("Are you sure you want to proceed? Type 'YES' to confirm: ")
            if confirmation != 'YES':
                print("❌ Operation cancelled")
                return
        except (EOFError, KeyboardInterrupt):
            print("❌ Operation cancelled")
            return
    
    print("🚀 Starting complete database wipe...")
    
    driver = get_driver()
    settings = Settings()
    
    try:
        async with driver.session(database=settings.neo4j_db) as session:
            # Step 1: Drop all constraints
            await drop_all_constraints(session)
            
            # Step 2: Drop all indexes
            await drop_all_indexes(session)
            
            # Step 3: Delete all data
            await delete_all_data(session)
            
    except Exception as e:
        print(f"❌ Error during database wipe: {e}")
        return
    finally:
        await driver.close()
    
    print("\n🎉 Database wipe complete!")
    print("✅ Database is now completely empty")
    print("✅ All constraints and indexes removed")
    print("✅ Ready for fresh data load")
    print()
    print("🚀 Next steps:")
    print("   1. make load-cim      # Load CIM asset data")
    print("   2. make load-fred     # Load FRED economic data")
    print("   3. make descriptions  # Generate descriptions")
    print("   4. make vectors       # Create vector embeddings")


if __name__ == "__main__":
    asyncio.run(wipe_database()) 